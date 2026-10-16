"use client";

import {
  useState,
} from "react";

import {
  FinancialFactTable,
} from "@/components/financial-facts/FinancialFactTable";


import {
  FinancialFactChartBuilder,
} from "@/components/financial-facts/FinancialFactChartBuilder";

export default function FactsPage() {
  const [
    input,
    setInput,
  ] = useState("");

  const [
    documentId,
    setDocumentId,
  ] = useState("");


  return (
    <main
      className="
        mx-auto max-w-7xl
        space-y-6 px-6 py-8
      "
    >
      <div>
        <h1
          className="
            text-2xl font-semibold
            tracking-tight
            text-slate-950
          "
        >
          Document Facts
        </h1>

        <p
          className="
            mt-1 text-sm
            text-slate-500
          "
        >
          Inspect validated,
          conflicted and rejected
          financial facts extracted
          from uploaded reports.
        </p>
      </div>


      <form
        className="
          flex max-w-3xl gap-2
        "
        onSubmit={(event) => {
          event.preventDefault();

          setDocumentId(
            input.trim(),
          );
        }}
      >
        <input
          value={input}
          onChange={(event) =>
            setInput(
              event.target.value,
            )
          }
          placeholder="Document ID"
          className="
            min-w-0 flex-1
            rounded-lg border
            border-slate-200
            px-3 py-2 text-sm
            outline-none
            focus:border-slate-400
          "
        />

        <button
          type="submit"
          className="
            rounded-lg
            bg-slate-900
            px-4 py-2
            text-sm font-medium
            text-white
            hover:bg-slate-800
          "
        >
          Load facts
        </button>
      </form>


      {documentId && (
        <div className="space-y-6">
          <FinancialFactChartBuilder
            documentId={
              documentId
            }
          />

          <FinancialFactTable
            documentId={
              documentId
            }
          />
        </div>
        )}
    </main>
  );
}