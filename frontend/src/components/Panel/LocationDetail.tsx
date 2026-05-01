import type { LocationDetail as LocationDetailType } from "@/types";

interface LocationDetailProps {
  location: LocationDetailType;
  onBack: () => void;
}

export function LocationDetail({ location, onBack }: LocationDetailProps) {
  return (
    <div className="h-full flex flex-col bg-white">
      <div className="flex items-center gap-2 p-3 border-b">
        <button onClick={onBack} className="p-1 hover:bg-gray-100 rounded">
          &larr;
        </button>
        <h2 className="font-bold text-base flex-1">{location.name}</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <p className="text-sm text-gray-500">详情页面加载中...</p>
      </div>
    </div>
  );
}
