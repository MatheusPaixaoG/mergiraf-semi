class User {
    var name: String
    var email: String
<<<<<<< left.swift
    var age: Int = 25
=======
    var age: Int = 30
>>>>>>> right.swift
    
    init(name: String, email: String) {
        self.name = name
        self.email = email
    }
    
    func getFullInfo() -> String {
        return "Name: \(name), Email: \(email)"
    }
}
