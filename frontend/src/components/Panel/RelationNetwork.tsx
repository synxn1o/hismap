import { useNavigate } from "react-router-dom";
import { ArrowRight, Network } from "lucide-react";
import type { LocationDetail as LocationDetailType } from "@/types";

interface RelationNetworkProps {
  location: LocationDetailType;
}

export function RelationNetwork({ location }: RelationNetworkProps) {
  const navigate = useNavigate();

  if (location.related_locations.length === 0) return null;

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-3">
        <Network className="h-5 w-5 text-gray-400" />
        <h2 className="text-lg font-bold">关系网络</h2>
      </div>
      <div className="space-y-2">
        {location.related_locations.map((rel) => (
          <button
            key={rel.id}
            onClick={() => navigate(`/locations/${rel.id}`)}
            className="w-full flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 transition-colors text-left"
          >
            <div>
              <p className="text-sm font-medium">{rel.name}</p>
              <p className="text-xs text-gray-500">{rel.relation_type}</p>
              {rel.description && (
                <p className="text-xs text-gray-400 mt-0.5">{rel.description}</p>
              )}
            </div>
            <ArrowRight className="h-4 w-4 text-gray-400" />
          </button>
        ))}
      </div>
    </div>
  );
}
