enum Status {
    case pending
    case active
    case completed
<<<<<<< left.swift
    case cancelled
=======
    case archived
>>>>>>> right.swift
}

class Task {
    var title: String
    var status: Status
    
    init(title: String) {
        self.title = title
        self.status = .pending
    }
}
