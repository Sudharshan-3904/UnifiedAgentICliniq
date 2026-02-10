export enum BMICategory {
    UNDERWEIGHT = "Underweight",
    NORMAL = "Normal weight",
    OVERWEIGHT = "Overweight",
    OBESE = "Obese"
}

export const BMICategoryInfo = {
    [BMICategory.UNDERWEIGHT]: { label: "Underweight", color: "#3498db" },
    [BMICategory.NORMAL]: { label: "Normal weight", color: "#2ecc71" },
    [BMICategory.OVERWEIGHT]: { label: "Overweight", color: "#f39c12" },
    [BMICategory.OBESE]: { label: "Obese", color: "#e74c3c" }
};

export interface BMIResult {
    bmi: number;
    category: BMICategory;
    height: number;
    weight: number;
}

export function calculateBMICore(height: number, weight: number): BMIResult {
    if (height <= 0 || weight <= 0) {
        throw new Error("Height and weight must be positive.");
    }
    const bmi = weight / (height * height);
    let category: BMICategory;

    if (bmi < 18.5) {
        category = BMICategory.UNDERWEIGHT;
    } else if (bmi < 25) {
        category = BMICategory.NORMAL;
    } else if (bmi < 30) {
        category = BMICategory.OVERWEIGHT;
    } else {
        category = BMICategory.OBESE;
    }

    return { bmi, category, height, weight };
}

export function renderWidget(result: BMIResult): string {
    const info = BMICategoryInfo[result.category];
    return `
    <div class="bmi-card" style="border-radius: 12px; overflow: hidden; font-family: sans-serif; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 350px; margin: 10px 0;">
        <div style="background: ${info.color}; padding: 15px; color: white; text-align: center;">
            <h3 style="margin: 0; font-size: 1.1rem;">BMI Health Advisor</h3>
        </div>
        <div style="padding: 20px; text-align: center;">
            <div style="font-size: 3rem; font-weight: 800; color: ${info.color}; line-height: 1;">${result.bmi.toFixed(1)}</div>
            <div style="color: #666; margin-top: 5px; font-weight: 600;">${info.label}</div>
            
            <div style="display: flex; justify-content: space-around; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">
                <div>
                    <div style="font-size: 0.7rem; color: #999; text-transform: uppercase;">Height</div>
                    <div style="font-weight: 600;">${result.height}m</div>
                </div>
                <div>
                    <div style="font-size: 0.7rem; color: #999; text-transform: uppercase;">Weight</div>
                    <div style="font-weight: 600;">${result.weight}kg</div>
                </div>
            </div>
        </div>
    </div>
    `;
}
