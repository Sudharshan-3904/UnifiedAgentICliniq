document.getElementById("bmi-form").addEventListener("submit", function (e) {
  e.preventDefault();

  const height = parseFloat(document.getElementById("height").value);
  const weight = parseFloat(document.getElementById("weight").value);

  if (height <= 0 || weight <= 0 || isNaN(height) || isNaN(weight)) {
    alert("Please enter valid positive numbers for height and weight.");
    return;
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

  const resultDiv = document.getElementById("result");
  const bmiValueP = document.getElementById("bmi-value");
  const bmiCategoryP = document.getElementById("bmi-category");

  bmiValueP.textContent = `Your BMI is ${bmiValue}`;
  bmiCategoryP.textContent = `Category: ${category}`;

  resultDiv.className = `result ${categoryClass}`;
  resultDiv.classList.remove("hidden");
});
