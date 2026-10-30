//! A small notes API: routing, extractors, shared state, an error type that
//! implements `IntoResponse`, layers, and tests that call the router directly.

use std::{
    collections::BTreeMap,
    sync::{Arc, Mutex},
    time::Duration,
};

use axum::{
    Json, Router,
    extract::{Path, Query, Request, State},
    http::{HeaderValue, StatusCode},
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::get,
};
use serde::{Deserialize, Serialize};
use tower_http::{timeout::TimeoutLayer, trace::TraceLayer};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Note {
    pub id: u64,
    pub title: String,
}

#[derive(Deserialize)]
pub struct NewNote {
    pub title: String,
}

#[derive(Deserialize)]
pub struct ListParams {
    #[serde(default)]
    pub contains: Option<String>,
}

#[derive(Default)]
pub struct Store {
    next_id: u64,
    notes: BTreeMap<u64, Note>,
}

/// Shared state: cheap to clone because it is an `Arc`.
pub type AppState = Arc<Mutex<Store>>;

/// The one error type handlers return. Each variant knows its status code.
#[derive(Debug)]
pub enum ApiError {
    NotFound(u64),
    Invalid(&'static str),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, msg) = match self {
            ApiError::NotFound(id) => (StatusCode::NOT_FOUND, format!("note {id} not found")),
            ApiError::Invalid(m) => (StatusCode::UNPROCESSABLE_ENTITY, m.to_string()),
        };
        (status, Json(serde_json::json!({ "error": msg }))).into_response()
    }
}

async fn list(State(s): State<AppState>, Query(p): Query<ListParams>) -> Json<Vec<Note>> {
    let store = s.lock().unwrap(); // std Mutex is fine: the guard is never held across .await
    let notes = store
        .notes
        .values()
        .filter(|n| {
            p.contains
                .as_ref()
                .is_none_or(|c| n.title.contains(c.as_str()))
        })
        .cloned()
        .collect();
    Json(notes)
}

async fn create(
    State(s): State<AppState>,
    Json(new): Json<NewNote>,
) -> Result<(StatusCode, Json<Note>), ApiError> {
    if new.title.trim().is_empty() {
        return Err(ApiError::Invalid("title must not be empty"));
    }
    let mut store = s.lock().unwrap();
    store.next_id += 1;
    let note = Note {
        id: store.next_id,
        title: new.title,
    };
    store.notes.insert(note.id, note.clone());
    Ok((StatusCode::CREATED, Json(note)))
}

async fn fetch(State(s): State<AppState>, Path(id): Path<u64>) -> Result<Json<Note>, ApiError> {
    s.lock()
        .unwrap()
        .notes
        .get(&id)
        .cloned()
        .map(Json)
        .ok_or(ApiError::NotFound(id))
}

async fn remove(State(s): State<AppState>, Path(id): Path<u64>) -> Result<StatusCode, ApiError> {
    s.lock()
        .unwrap()
        .notes
        .remove(&id)
        .map(|_| StatusCode::NO_CONTENT)
        .ok_or(ApiError::NotFound(id))
}

async fn slow() -> &'static str {
    tokio::time::sleep(Duration::from_secs(5)).await;
    "done"
}

/// A hand-written middleware: adds a header to every response.
async fn add_version_header(req: Request, next: Next) -> Response {
    let mut res = next.run(req).await;
    res.headers_mut()
        .insert("x-api-version", HeaderValue::from_static("1"));
    res
}

pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/notes", get(list).post(create))
        .route("/notes/{id}", get(fetch).delete(remove))
        .route("/slow", get(slow))
        .layer(middleware::from_fn(add_version_header))
        .layer(TimeoutLayer::with_status_code(
            StatusCode::REQUEST_TIMEOUT,
            Duration::from_millis(200),
        ))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Method, Request};
    use http_body_util::BodyExt;
    use tower::ServiceExt; // for `oneshot`

    async fn call(
        app: &Router,
        method: Method,
        uri: &str,
        body: Option<&str>,
    ) -> (StatusCode, String, Option<String>) {
        let mut b = Request::builder().method(method).uri(uri);
        let body = match body {
            Some(j) => {
                b = b.header("content-type", "application/json");
                Body::from(j.to_owned())
            }
            None => Body::empty(),
        };
        let res = app.clone().oneshot(b.body(body).unwrap()).await.unwrap();
        let status = res.status();
        let ver = res
            .headers()
            .get("x-api-version")
            .map(|v| v.to_str().unwrap().to_owned());
        let bytes = res.into_body().collect().await.unwrap().to_bytes();
        (status, String::from_utf8(bytes.to_vec()).unwrap(), ver)
    }

    #[tokio::test]
    async fn crud_round_trip() {
        let app = app(AppState::default());
        let (s, body, ver) = call(&app, Method::POST, "/notes", Some(r#"{"title":"first"}"#)).await;
        assert_eq!(s, StatusCode::CREATED);
        assert_eq!(ver.as_deref(), Some("1"));
        assert_eq!(body, r#"{"id":1,"title":"first"}"#);
        let (s, body, _) = call(&app, Method::GET, "/notes?contains=fir", None).await;
        assert_eq!(
            (s, body.as_str()),
            (StatusCode::OK, r#"[{"id":1,"title":"first"}]"#)
        );
        assert_eq!(
            call(&app, Method::DELETE, "/notes/1", None).await.0,
            StatusCode::NO_CONTENT
        );
        let (s, body, _) = call(&app, Method::GET, "/notes/1", None).await;
        assert_eq!(
            (s, body.as_str()),
            (StatusCode::NOT_FOUND, r#"{"error":"note 1 not found"}"#)
        );
    }

    #[tokio::test]
    async fn extractor_rejections() {
        let app = app(AppState::default());
        assert_eq!(
            call(&app, Method::POST, "/notes", Some(r#"{"title":" "}"#))
                .await
                .0,
            StatusCode::UNPROCESSABLE_ENTITY
        );
        assert_eq!(
            call(&app, Method::POST, "/notes", Some("not json")).await.0,
            StatusCode::BAD_REQUEST
        ); // invalid JSON syntax
        assert_eq!(
            call(&app, Method::POST, "/notes", Some(r#"{"name":"x"}"#))
                .await
                .0,
            StatusCode::UNPROCESSABLE_ENTITY
        ); // valid JSON, missing field
        assert_eq!(
            call(&app, Method::GET, "/notes/abc", None).await.0,
            StatusCode::BAD_REQUEST
        );
        assert_eq!(
            call(&app, Method::PUT, "/notes", None).await.0,
            StatusCode::METHOD_NOT_ALLOWED
        );
    }

    #[tokio::test(start_paused = true)]
    async fn slow_handler_times_out() {
        let app = app(AppState::default());
        assert_eq!(
            call(&app, Method::GET, "/slow", None).await.0,
            StatusCode::REQUEST_TIMEOUT
        );
    }
}
