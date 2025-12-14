class User {
    var name: String
    var email: String
    
    init(name: String, email: String) {
        self.name = name
        self.email = email
    }
    
    func getFullInfo() -> String {
        return "Name: \(name), Email: \(email)"
    }
}
