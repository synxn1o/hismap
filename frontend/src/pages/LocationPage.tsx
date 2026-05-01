import { useParams, useNavigate } from "react-router-dom";
import { useLocation } from "@/api/hooks";
import { LocationDetail } from "@/components/Panel/LocationDetail";

export function LocationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: location, isLoading } = useLocation(Number(id));

  if (isLoading) {
    return <div className="h-full flex items-center justify-center">加载中...</div>;
  }

  if (!location) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <p className="text-gray-500">地点未找到</p>
        <button onClick={() => navigate("/")} className="text-blue-600 underline">返回地图</button>
      </div>
    );
  }

  return <LocationDetail location={location} onBack={() => navigate("/")} />;
}
