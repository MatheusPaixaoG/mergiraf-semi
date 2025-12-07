class Settings {
    var volume: Int = 5 {
        didSet {
            print("New volume: \(volume)")
        }
    }

    func reset() {
        volume = 5
    }
}