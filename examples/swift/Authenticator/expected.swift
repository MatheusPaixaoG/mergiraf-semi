struct User {
    let name: String
}

class Authenticator {
    func authenticate(username: String, password: String) -> User? {
        if username == "admin" && password == "s3cr3t" {
            return User(name: "admin")
        } else {
            return nil
        }
    }
}