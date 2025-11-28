struct Person {
    var id: String
    var name: String
    var nicknames: [String] = ["Ada"] {
        willSet {
            print("Will set nicknames to \(newValue)")
        }
        didSet {
            print("Did set nicknames from \(oldValue)")
        }
    }
}
