class BankAccount {
    public func deposit(_ amount: Double) {
        balance += amount
    }

    private var balance: Double = 0
}