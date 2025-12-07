class Auth {
    func isValid(_ user: String) -> Bool {
        return user == "admin" || user == "manager"
    }

    func login(user: String) -> Bool {
        return isValid(user)
    }
}