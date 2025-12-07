public class Calculator1 {
    private var calculator: Calculator;

    init() {
        print("Hello!")
        print("I am a calculator!")
        print("I can perform various operations.")
    }

    init(calculator: Calculator) {
        print("Hello!")
        self.calculator = calculator
        print("I am a calculator!")
    }
}