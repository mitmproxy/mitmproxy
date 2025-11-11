import type React from "react";
import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { FILTER_DEFINITIONS } from "./constants";
import type { FilterCommand } from "./types";
import { FilterDescription } from "./filter-description";
import { Label } from "@/components/ui/label";

export type FilterInputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  label?: string;
  hideDescription?: boolean;
};

export function FilterInput({
  onChange,
  value,
  placeholder,
  className,
  label,
  hideDescription = false,
}: FilterInputProps) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState(0);
  const [cursorPosition, setCursorPosition] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  const getCurrentWord = () => {
    const beforeCursor = value.slice(0, cursorPosition);
    const afterCursor = value.slice(cursorPosition);
    const wordStart =
      Math.max(
        beforeCursor.lastIndexOf(" "),
        beforeCursor.lastIndexOf("("),
        beforeCursor.lastIndexOf("&"),
        beforeCursor.lastIndexOf("|"),
      ) + 1;
    const wordEnd = Math.min(
      afterCursor.search(/[\s&|()]/),
      afterCursor.length,
    );
    const currentWord =
      beforeCursor.slice(wordStart) +
      (wordEnd === -1 ? afterCursor : afterCursor.slice(0, wordEnd));
    return {
      word: currentWord,
      start: wordStart,
      end: wordStart + currentWord.length,
    };
  };

  const getSuggestions = () => {
    const { word } = getCurrentWord();
    if (!word || word.length < 1) return [];

    return Object.values(FILTER_DEFINITIONS)
      .filter(
        (command) =>
          command.symbol.toLowerCase().includes(word.toLowerCase()) ||
          command.description.toLowerCase().includes(word.toLowerCase()),
      )
      .slice(0, 8);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const suggestions = getSuggestions();

    if (e.key === "ArrowDown") {
      e.preventDefault();
      const newIndex = Math.min(selectedSuggestion + 1, suggestions.length - 1);
      setSelectedSuggestion(newIndex);
      scrollToSuggestion(newIndex);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const newIndex = Math.max(selectedSuggestion - 1, 0);
      setSelectedSuggestion(newIndex);
      scrollToSuggestion(newIndex);
    } else if (e.key === "Tab" || e.key === "Enter") {
      if (showSuggestions && suggestions.length > 0) {
        e.preventDefault();
        applySuggestion(suggestions[selectedSuggestion]);
      }
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  const scrollToSuggestion = (index: number) => {
    setTimeout(() => {
      const suggestionElement = suggestionsRef.current?.children[
        index
      ] as HTMLElement;
      if (suggestionElement) {
        suggestionElement.scrollIntoView({ block: "nearest" });
      }
    }, 0); // Delay to ensure the DOM is updated.
  };

  const applySuggestion = (suggestion: FilterCommand) => {
    const { word, start } = getCurrentWord();
    const beforeWord = value.slice(0, start);
    const afterWord = value.slice(start + word.length);

    let newFilter = beforeWord + suggestion.symbol;
    if (suggestion.hasValue) {
      newFilter += ' ""';
    }
    newFilter += afterWord;

    onChange(newFilter);
    setShowSuggestions(false);

    // Set cursor position.
    setTimeout(() => {
      if (inputRef.current) {
        const newPosition =
          beforeWord.length +
          suggestion.symbol.length +
          (suggestion.hasValue ? 2 : 0);
        inputRef.current.setSelectionRange(newPosition, newPosition);
        setCursorPosition(newPosition);
      }
    }, 0); // Delay to ensure the DOM is updated.
  };

  const handleInputChange = (newValue: string) => {
    onChange(newValue);
    setShowSuggestions(newValue.length > 0);
    setSelectedSuggestion(0);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const suggestions = getSuggestions();

  return (
    <div className="flex h-full flex-col">
      <div className="relative flex-1">
        <div className="flex flex-col gap-2">
          {label && <Label htmlFor="filter-input">{label}</Label>}
          <Input
            ref={inputRef}
            id="filter-input"
            value={value}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowSuggestions(value.length > 0)}
            onSelect={(e) =>
              setCursorPosition(
                (e.target as HTMLInputElement).selectionStart || 0,
              )
            }
            placeholder={placeholder}
            className={cn("font-mono text-sm", className)}
          />
        </div>
        {showSuggestions && suggestions.length > 0 && (
          <div
            ref={suggestionsRef}
            className={cn(
              "bg-background absolute right-0 left-0 z-50 mt-1 max-h-80 overflow-y-auto rounded-md border shadow-lg",
              label ? "top-16" : "top-10",
            )}
          >
            {suggestions.map((suggestion, index) => (
              <div
                key={suggestion.symbol}
                className={`cursor-pointer border-b px-3 py-2 last:border-b-0 ${
                  index === selectedSuggestion
                    ? "bg-accent/50"
                    : "hover:bg-accent/30"
                }`}
                onClick={() => applySuggestion(suggestion)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <code className="text-primary font-mono text-sm">
                      {suggestion.symbol}
                    </code>
                  </div>
                </div>
                <p className="text-muted-foreground mt-1 text-xs">
                  {suggestion.description}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
      {!hideDescription && <FilterDescription filter={value} />}
    </div>
  );
}
