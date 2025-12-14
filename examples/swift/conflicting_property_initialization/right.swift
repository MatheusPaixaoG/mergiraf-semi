class User {
    var name: String
    var email: String
    var age: Int = 30
    
    init(name: String, email: String) {
        self.name = name
        self.email = email
    }
    
    func getFullInfo() -> String {
        return "Name: \(name), Email: \(email)"
    }
}
