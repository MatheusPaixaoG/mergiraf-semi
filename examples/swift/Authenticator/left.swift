class Authenticator {
    func authenticate(username: String, password: String) -> Bool {
        return username == "admin" && password == "s3cr3t"
    }
}