struct User {
    let name: String
}

class Authenticator {
<<<<<<< LEFT
    func authenticate(username: String, password: String) -> Bool {
        // check username and password
        return username == "admin" && password == "s3cr3t"
    }
=======
    func authenticate(user: String) -> User? {
        // modern token-based auth (returns a user on success)
        if user == "admin" {
            return User(name: "admin")
        } else {
            return nil
        }
    }
>>>>>>> RIGHT
}