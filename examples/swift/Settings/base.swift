class Settings {
    var volume: Int = 5 {
        didSet {
            print("Volume changed")
        }
    }

    func reset() {
        volume = 5
    }
}