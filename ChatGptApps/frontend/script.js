document.addEventListener("DOMContentLoaded", function () {
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const chatMessages = document.getElementById("chat-messages");

  function addMessage(content, isUser = false) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${isUser ? "user-message" : "bot-message"}`;

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.innerHTML = content;

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function parseBMIRequest(text) {
    // regex match to find the height and weight
    const lowerText = text.toLowerCase();
    const heightMatch = lowerText.match(/height\s+(\d+(?:\.\d+)?)/);
    const weightMatch = lowerText.match(/weight\s+(\d+(?:\.\d+)?)/);

    if (heightMatch && weightMatch) {
      const height = parseFloat(heightMatch[1]);
      const weight = parseFloat(weightMatch[1]);
      return { height, weight };
    }
    return null;
  }

  function calculateBMI(height, weight) {
    if (height <= 0 || weight <= 0 || isNaN(height) || isNaN(weight)) {
      return {
        error: "Please provide valid positive numbers for height and weight.",
      };
    }

    const bmi = weight / (height * height);
    const bmiValue = bmi.toFixed(2);

    let category = "";
    let categoryClass = "";

    if (bmi < 18.5) {
      category = "Underweight";
      categoryClass = "underweight";
    } else if (bmi < 25) {
      category = "Normal weight";
      categoryClass = "normal";
    } else if (bmi < 30) {
      category = "Overweight";
      categoryClass = "overweight";
    } else {
      category = "Obese";
      categoryClass = "obese";
    }

    return {
      bmi: bmiValue,
      category,
      categoryClass,
      height,
      weight,
    };
  }

  function createBMIWidget(result) {
    return `
      <div class="bmi-widget ${result.categoryClass}">
        <h3>Your BMI Result</h3>
        <div class="bmi-value">BMI: ${result.bmi}</div>
        <div class="bmi-category">Category: ${result.category}</div>
        <div style="font-size: 0.8rem; color: #666; margin-top: 0.5rem;">
          Height: ${result.height} m | Weight: ${result.weight} kg
        </div>
      </div>
    `;
  }

  function handleUserInput() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, true);
    userInput.value = "";

    const bmiRequest = parseBMIRequest(text);
    if (bmiRequest) {
      const result = calculateBMI(bmiRequest.height, bmiRequest.weight);
      if (result.error) {
        addMessage(result.error);
      } else {
        const widget = createBMIWidget(result);
        addMessage(widget);
      }
    } else {
      addMessage(
        "I can help you calculate your BMI. Try typing something like 'calculate bmi height 1.75 weight 70'.",
      );
    }
  }

  sendButton.addEventListener("click", handleUserInput);
  userInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      handleUserInput();
    }
  });
});
