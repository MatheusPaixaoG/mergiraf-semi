protocol Drawable {
    func draw()
}

class Circle: Drawable {
    var radius: Double
    
    init(radius: Double) {
        self.radius = radius
    }
    
    func draw() {
        print("Drawing circle")
    }
}
