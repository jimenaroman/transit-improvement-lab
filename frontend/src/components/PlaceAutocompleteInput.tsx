import { useEffect, useRef, useState } from 'react'
import { CheckIcon } from 'lucide-react'
import { fetchPlaceAutocomplete } from '@/api'
import type { LocationInput, PlaceSuggestion } from '@/types'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

const DEBOUNCE_MS = 300
const MIN_QUERY_LENGTH = 3

interface PlaceAutocompleteInputProps {
  placeholder: string
  value: LocationInput
  onChange: (value: LocationInput) => void
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}

// Custom dropdown rather than the shadcn Popover/Command pair -- those
// assume a button trigger, and this needs a plain text input as the anchor.
export function PlaceAutocompleteInput({ placeholder, value, onChange }: PlaceAutocompleteInputProps) {
  const [query, setQuery] = useState(value.label)
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const [unavailable, setUnavailable] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const debouncedQuery = useDebouncedValue(query, DEBOUNCE_MS)

  const confirmed = Boolean(value.place_id)

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  useEffect(() => {
    // No fetch below the minimum length; the render guard below (which
    // checks the immediate, non-debounced query) hides any stale
    // suggestions instantly rather than waiting on a cleared state here.
    if (debouncedQuery.trim().length < MIN_QUERY_LENGTH) {
      return
    }

    let cancelled = false

    fetchPlaceAutocomplete(debouncedQuery)
      .then((results) => {
        if (cancelled) return
        setSuggestions(results)
        setOpen(results.length > 0)
        setHighlightedIndex(-1)
        setUnavailable(false)
      })
      .catch(() => {
        // A 502 here almost always means Places API (New) isn't enabled yet
        // -- degrade to the raw-text fallback rather than erroring visibly.
        if (cancelled) return
        setSuggestions([])
        setUnavailable(true)
      })

    return () => {
      cancelled = true
    }
  }, [debouncedQuery])

  function handleInputChange(text: string) {
    setQuery(text)
    // Typing invalidates a previously selected place_id -- the label no
    // longer matches what was picked, so routing falls back to raw text.
    onChange({ label: text })
  }

  function handleSelect(suggestion: PlaceSuggestion) {
    setQuery(suggestion.label)
    onChange({ label: suggestion.label, place_id: suggestion.place_id })
    setOpen(false)
    setSuggestions([])
    setHighlightedIndex(-1)
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlightedIndex((index) => (index + 1) % suggestions.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlightedIndex((index) => (index <= 0 ? suggestions.length - 1 : index - 1))
    } else if (event.key === 'Enter' && highlightedIndex >= 0) {
      event.preventDefault()
      handleSelect(suggestions[highlightedIndex])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  const showDropdown = open && query.trim().length >= MIN_QUERY_LENGTH && suggestions.length > 0

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1">
      <div className="relative">
        <Input
          placeholder={placeholder}
          value={query}
          onChange={(event) => handleInputChange(event.target.value)}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          role="combobox"
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          className={cn(confirmed && 'border-primary/60 pr-8')}
        />
        {confirmed && (
          <CheckIcon
            aria-hidden
            className="absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-primary"
          />
        )}
      </div>

      {!confirmed && query.trim().length > 0 && !showDropdown && (
        <span className="font-mono text-[10px] text-(--neutral-700)">
          {unavailable ? 'Autocomplete unavailable — enter a full address' : 'Unverified — select a suggestion or enter a full address'}
        </span>
      )}

      {showDropdown && (
        <div className="absolute top-full z-50 mt-1.5 w-full overflow-hidden rounded-lg border border-border bg-popover shadow-md">
          {suggestions.map((suggestion, index) => (
            <button
              key={suggestion.place_id}
              type="button"
              onClick={() => handleSelect(suggestion)}
              onMouseEnter={() => setHighlightedIndex(index)}
              role="option"
              aria-selected={index === highlightedIndex}
              className={cn(
                'flex w-full flex-col gap-0.5 px-3 py-2 text-left',
                index === highlightedIndex ? 'bg-muted' : 'hover:bg-muted',
              )}
            >
              <span className="text-[13px] text-(--neutral-200)">{suggestion.primary_text}</span>
              {suggestion.secondary_text && (
                <span className="text-xs text-(--neutral-600)">{suggestion.secondary_text}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
