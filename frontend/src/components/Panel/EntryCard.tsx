import React, { useState } from "react";
import type { JournalEntryDetail } from "@/types";

type TranslationTab = "original" | "excerpt" | "summary";

interface EntryCardProps {
  entry: JournalEntryDetail;
}

export function EntryCard({ entry }: EntryCardProps) {
  const [activeTab, setActiveTab] = useState<TranslationTab>("original");

  const tabs: { key: TranslationTab; label: string; available: boolean }[] = [
    { key: "original", label: "原文", available: true },
    { key: "excerpt", label: "Excerpt", available: !!entry.excerpt_original },
    { key: "summary", label: "Summary", available: !!(entry.summary_chinese || entry.summary_english) },
  ];

  const availableTabs = tabs.filter((t) => t.available);

  const activeContent: Record<TranslationTab, React.ReactNode> = {
    original: entry.original_text,
    excerpt: entry.excerpt_original
      ? entry.excerpt_translation
        ? `${entry.excerpt_original}\n\n${entry.excerpt_translation}`
        : entry.excerpt_original
      : null,
    summary: entry.summary_chinese
      ? entry.summary_english
        ? `${entry.summary_chinese}\n\n${entry.summary_english}`
        : entry.summary_chinese
      : entry.summary_english,
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
