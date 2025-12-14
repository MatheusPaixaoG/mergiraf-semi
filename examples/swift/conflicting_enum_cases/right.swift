enum Status {
    case pending
    case active
    case completed
    case archived
}

class Task {
    var title: String
    var status: Status
    
    init(title: String) {
        self.title = title
        self.status = .pending
    }
}
