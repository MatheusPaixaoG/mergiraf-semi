struct User {
    let name: String
}

class Authenticator {
    func authenticate(user: String) -> User? {
        if user == "admin" {
            return User(name: "admin")
        } else {
            return nil
        }
    }
}