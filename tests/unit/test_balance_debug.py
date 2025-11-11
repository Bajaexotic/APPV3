"""
Balance Debug Test Script
Tests the balance update flow and provides manual balance setting for SIM mode
"""

import sys

from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from core.data_bridge import signal_balance
from utils.logger import get_logger


log = get_logger(__name__)


class BalanceDebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Balance Debug Tool")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        # Title
        title = QLabel("Balance Update Debug Tool")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        # Balance input
        input_label = QLabel("Manual Balance (for SIM mode):")
        layout.addWidget(input_label)

        self.balance_input = QLineEdit()
        self.balance_input.setText("")  # No default - use actual account balance
        self.balance_input.setPlaceholderText("Enter balance amount")
        layout.addWidget(self.balance_input)

        # Send button
        send_btn = QPushButton("Send Balance Update")
        send_btn.clicked.connect(self.send_balance)
        layout.addWidget(send_btn)

        # Test values buttons
        test_layout = QVBoxLayout()

        btn1 = QPushButton("Test: $50,000")
        btn1.clicked.connect(lambda: self.send_test_balance(50000.00))
        test_layout.addWidget(btn1)

        btn2 = QPushButton("Test: $25,500.50")
        btn2.clicked.connect(lambda: self.send_test_balance(25500.50))
        test_layout.addWidget(btn2)

        btn3 = QPushButton("Test: $5,123.75")
        btn3.clicked.connect(lambda: self.send_test_balance(5123.75))
        test_layout.addWidget(btn3)

        layout.addLayout(test_layout)

        # Listen for balance signals
        signal_balance.connect(self.on_balance_received)

        self.setLayout(layout)

        log.info("Balance debug window initialized")

    def send_balance(self):
        """Send a manual balance update"""
        try:
            balance = float(self.balance_input.text())
            log.info(f"[DEBUG] Manually sending balance: ${balance:,.2f}")

            # Emit signal just like DTC would
            payload = {
                "balance": balance,
                "AccountValue": balance,
                "CashBalance": balance,
                "NetLiquidatingValue": balance,
                "AvailableFunds": balance,
            }

            log.info(f"[DEBUG] Emitting signal_balance with payload: {payload}")
            signal_balance.send(payload)

            self.status_label.setText(f"✅ Sent: ${balance:,.2f}")
            self.status_label.setStyleSheet("color: green;")

        except ValueError as e:
            self.status_label.setText("❌ Error: Invalid number")
            self.status_label.setStyleSheet("color: red;")
            log.error(f"[DEBUG] Invalid balance input: {e}")
        except Exception as e:
            self.status_label.setText(f"❌ Error: {e}")
            self.status_label.setStyleSheet("color: red;")
            log.error(f"[DEBUG] Error sending balance: {e}", exc_info=True)

    def send_test_balance(self, amount: float):
        """Send a test balance"""
        self.balance_input.setText(str(amount))
        self.send_balance()

    def on_balance_received(self, msg: dict):
        """Callback when balance signal is received (echo back)"""
        balance = msg.get("balance")
        log.info(f"[DEBUG] ✅ Received balance signal echo: {balance}")
        print(f"✅ Balance signal received: ${balance:,.2f}" if balance else "❌ Balance is None!")


if __name__ == "__main__":
    print("=" * 60)
    print("Balance Debug Tool")
    print("=" * 60)
    print()
    print("This tool helps debug balance update flow:")
    print("  1. Click buttons to send test balance updates")
    print("  2. Watch the console for detailed logging")
    print("  3. Check if Panel 1 in main app updates")
    print()
    print("For SIM mode: Use this to manually set balance")
    print("since Sierra Chart SIM doesn't send balance updates")
    print()
    print("=" * 60)
    print()

    app = QApplication(sys.argv)
    window = BalanceDebugWindow()
    window.show()
    sys.exit(app.exec())
