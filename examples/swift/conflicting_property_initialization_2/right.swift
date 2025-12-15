class ViewConfiguration {
    var backgroundColor: String
    var cornerRadius: Double
    
    init() {
        self.backgroundColor = "white"
        self.cornerRadius = 16.0
    }
    
    func applyStyle() {
        print("Applying style with background: \(backgroundColor)")
    }
}
