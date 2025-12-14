enum Status {
    case pending
    case active
    case completed
}

class Task {
    var title: String
    var status: Status
    
    init(title: String) {
        self.title = title
        self.status = .pending
    }
}
