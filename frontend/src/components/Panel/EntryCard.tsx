import { useState } from "react";
import type { JournalEntryDetail } from "@/types";

type TranslationTab = "original" | "english" | "modern";

interface EntryCardProps {
  entry: JournalEntryDetail;
}

export function EntryCard({ entry }: EntryCardProps) {
  const [activeTab, setActiveTab] = useState<TranslationTab>("original");

  const tabs: { key: TranslationTab; label: string; available: boolean }[] = [
    { key: "original", label: "原文", available: true },
    { key: "english", label: "English", available: !!entry.english_translation },
    { key: "modern", label: "白话译文", available: !!entry.modern_translation },
  ];

  const availableTabs = tabs.filter((t) => t.available);

  const activeContent: Record<TranslationTab, string | null> = {
    original: entry.original_text,
    english: entry.english_translation,
    modern: entry.modern_translation,
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-3 bg-gray-50 border-b">
        <div className="flex items-center justify-between">
          <div>
            {entry.authors.map((a) => (
              <span key={a.id} className="text-sm font-medium mr-2">{a.name}</span>
            ))}
            {entry.visit_date_approximate && (
              <span className="text-xs text-gray-400">{entry.visit_date_approximate}年</span>
            )}
          </div>
        </div>
        {entry.book && (
          <p className="text-xs text-gray-500 mt-0.5">
            《{entry.book.title}》{entry.chapter_reference && ` ${entry.chapter_reference}`}
          </p>
        )}
      </div>

      {/* Tabs */}
      {availableTabs.length > 1 && (
        <div className="flex border-b">
          {availableTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm ${
                activeTab === tab.key
                  ? "border-b-2 border-blue-500 text-blue-600 font-medium"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="p-3">
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {activeContent[activeTab]}
        </p>
      </div>

      {/* Keywords */}
      {entry.keywords && entry.keywords.length > 0 && (
        <div className="px-3 pb-3">
          <div className="flex flex-wrap gap-1">
            {entry.keywords.map((kw) => (
              <span key={kw} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
