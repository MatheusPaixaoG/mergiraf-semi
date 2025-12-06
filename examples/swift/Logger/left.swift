class Logger {
    var level: Int = 1

    func log(_ msg: String) {
        print(msg)
    }

    func warn(_ msg: String) {
        print("WARN: \(msg)")
    }
}