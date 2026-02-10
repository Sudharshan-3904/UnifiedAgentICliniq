import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Scale, Ruler, Info, Target } from 'lucide-react';

interface BMIResultData {
    bmi: number;
    category: string;
    color: string;
    height: number;
    weight: number;
    ideal_weight_min: number;
    ideal_weight_max: number;
}

interface BMIWidgetProps {
    data: BMIResultData;
}

const BMIWidget: React.FC<BMIWidgetProps> = ({ data }) => {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="max-w-md w-full bg-white rounded-3xl shadow-2xl overflow-hidden border border-gray-100 font-sans"
        >
            <div
                className="px-8 py-6 text-white flex justify-between items-center"
                style={{ backgroundColor: data.color }}
            >
                <div>
                    <h2 className="text-2xl font-black uppercase tracking-tight">Health Status</h2>
                    <p className="text-white/80 text-sm font-medium">BMI Analysis Result</p>
                </div>
                <Activity size={32} className="opacity-80" />
            </div>

            <div className="p-8">
                <div className="flex flex-col items-center mb-8">
                    <motion.div
                        initial={{ rotate: -10 }}
                        animate={{ rotate: 0 }}
                        className="text-7xl font-black mb-2 transition-colors duration-500"
                        style={{ color: data.color }}
                    >
                        {data.bmi.toFixed(1)}
                    </motion.div>
                    <div
                        className="px-6 py-1.5 rounded-full text-white text-sm font-bold uppercase tracking-widest shadow-lg"
                        style={{ backgroundColor: data.color }}
                    >
                        {data.category}
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="bg-gray-50 p-4 rounded-2xl border border-gray-100">
                        <div className="flex items-center gap-2 mb-1 text-gray-500">
                            <Ruler size={14} />
                            <span className="text-[10px] font-bold uppercase tracking-wider">Height</span>
                        </div>
                        <div className="text-xl font-bold text-gray-800">{data.height}m</div>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-2xl border border-gray-100">
                        <div className="flex items-center gap-2 mb-1 text-gray-500">
                            <Scale size={14} />
                            <span className="text-[10px] font-bold uppercase tracking-wider">Weight</span>
                        </div>
                        <div className="text-xl font-bold text-gray-800">{data.weight}kg</div>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="flex items-start gap-4 p-4 bg-blue-50/50 rounded-2xl border border-blue-100">
                        <Target className="text-blue-500 shrink-0 mt-1" size={20} />
                        <div>
                            <div className="text-[10px] font-bold text-blue-600 uppercase tracking-widest mb-1">Ideal Weight Range</div>
                            <div className="text-sm font-bold text-blue-900">
                                {data.ideal_weight_min}kg - {data.ideal_weight_max}kg
                            </div>
                        </div>
                    </div>

                    <div className="flex items-start gap-4 p-4 bg-amber-50/50 rounded-2xl border border-amber-100">
                        <Info className="text-amber-500 shrink-0 mt-1" size={20} />
                        <p className="text-xs text-amber-900 leading-relaxed">
                            Maintain a balanced diet and regular physical activity to reach your target range.
                        </p>
                    </div>
                </div>
            </div>

            <div className="bg-gray-50 px-8 py-4 text-[10px] text-center text-gray-400 font-bold uppercase tracking-[0.2em] border-t border-gray-100">
                Clinical Reference: WHO Standards
            </div>
        </motion.div>
    );
};

export default BMIWidget;
