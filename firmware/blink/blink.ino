// Blink the SuperMini's onboard blue LED (GPIO8, lit when LOW) to identify the board.
const int LED_PIN = 8;

void setup() {
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_PIN, LOW);   // on
  delay(150);
  digitalWrite(LED_PIN, HIGH);  // off
  delay(150);
}
