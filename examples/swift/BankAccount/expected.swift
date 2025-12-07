class BankAccount {
    public func deposit(_ amount: Double) {
        if amount > 10 {
            balance += amount
        }
    }

    private var balance: Double = 0
}