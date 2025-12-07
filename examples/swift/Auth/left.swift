class Auth {
    func isValid(_ user: String) -> Bool {
        return user == "admin"
    }

    func login(user: String) -> Bool {
        return isValid(user)
    }
}