class Service {
    @discardableResult
    func fetch(id: Int, verbose: Bool) -> String {
        return verbose ? "item details" : "item"
    }
}