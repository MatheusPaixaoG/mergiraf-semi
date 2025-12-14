protocol Drawable {
    func draw()
    func erase()
}

class Circle: Drawable {
    var radius: Double
    
    init(radius: Double) {
        self.radius = radius
    }
    
    func draw() {
        print("Drawing circle")
    }
    
    func erase() {
        print("Clearing circle area")
    }
}
