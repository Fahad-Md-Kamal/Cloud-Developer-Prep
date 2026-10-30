//! Capstone 5: an async chat server. This file holds the pure, runtime-free core
//! (room state and message routing) so it is easy to test. Wrap it with Tokio:
//! one task per client, a `broadcast` or `mpsc` channel, graceful shutdown.
//! Add the runtime yourself: `cargo add tokio --features full`.

use std::collections::HashMap;

pub type ClientId = u64;

#[derive(Debug, PartialEq, Eq)]
pub enum Event {
    Joined(String),
    Left(String),
    Said { from: String, text: String },
}

#[derive(Default)]
pub struct Room {
    // Fields are yours to design (names by id, ordered history, ...).
    _names: HashMap<ClientId, String>,
}

impl Room {
    /// Register a client. Returns the events to broadcast. Reject a duplicate name.
    pub fn join(&mut self, _id: ClientId, _name: &str) -> Result<Vec<Event>, String> {
        todo!()
    }
    pub fn leave(&mut self, _id: ClientId) -> Vec<Event> {
        todo!()
    }
    /// Turn a line typed by a client into events. A line starting with `/` is a command (`/who`).
    pub fn say(&mut self, _id: ClientId, _line: &str) -> Vec<Event> {
        todo!()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore = "c05: implement Room"]
    fn c05_join_say_leave() {
        let mut room = Room::default();
        assert_eq!(room.join(1, "ana").unwrap(), [Event::Joined("ana".into())]);
        assert_eq!(
            room.say(1, "hi"),
            [Event::Said {
                from: "ana".into(),
                text: "hi".into()
            }]
        );
        assert_eq!(room.leave(1), [Event::Left("ana".into())]);
    }

    #[test]
    #[ignore = "c05: implement Room"]
    fn c05_duplicate_name_rejected() {
        let mut room = Room::default();
        room.join(1, "ana").unwrap();
        assert!(room.join(2, "ana").is_err());
    }
}
