class Settings {
    func reset() {
        volume = 5
    }

    var volume: Int = 5 {
        didSet {
            print("Volume changed")
        }
    }
}