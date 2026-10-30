#[tokio::main]
async fn main() {
    let name = String::from("demo");
    let h = tokio::spawn(async {
        println!("{name}");
    });
    h.await.unwrap();
}
