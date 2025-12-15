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
<<<<<<< left.swift
        print("Erasing with background color")
=======
        print("Clearing circle area")
>>>>>>> right.swift
    }
}
