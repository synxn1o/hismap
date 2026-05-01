import { MapPin, AlertTriangle, CheckCircle, HelpCircle } from "lucide-react";
import type { LocationDetail as LocationDetailType } from "@/types";

interface ModernExplanationProps {
  location: LocationDetailType;
}

export function ModernExplanation({ location }: ModernExplanationProps) {
  const sections = [
    { title: "古今对应", icon: MapPin, content: location.location_rationale },
    { title: "学术争议", icon: AlertTriangle, content: location.academic_disputes },
    { title: "可信度分析", icon: CheckCircle, content: location.credibility_notes },
    { title: "今日遗迹", icon: HelpCircle, content: location.today_remains },
  ].filter((s) => s.content);

  if (sections.length === 0) return null;

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-3">现代解释</h2>
      <div className="space-y-3">
        {sections.map((section) => (
          <div key={section.title} className="border rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <section.icon className="h-4 w-4 text-gray-400" />
              <h3 className="text-sm font-medium">{section.title}</h3>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{section.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
