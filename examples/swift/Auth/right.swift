class Auth {
    func login(user: String) -> Bool {
        return user == "admin" || user == "manager"
    }
}