func checkValue(_ value: Int?) {
    guard let unwrappedValue = value else {
        print("Value is nil")
        return // Added return statement
    }
    print("Value is \(unwrappedValue)")
}

// Call the function to demonstrate the issue (optional)
checkValue(nil)
checkValue(5)
