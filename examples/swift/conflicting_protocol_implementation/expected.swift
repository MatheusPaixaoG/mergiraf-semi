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
    
<<<<<<< left.swift
    func erase() {
        print("Erasing with background color")
    }
=======
    func erase() {
        print("Clearing circle area")
    }
>>>>>>> right.swift
}
