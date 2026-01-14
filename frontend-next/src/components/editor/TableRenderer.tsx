'use client';

import { Card } from '@/components/ui/card';
import type { Table } from '@/types';

interface TableRendererProps {
  table: Table;
}

export function TableRenderer({ table }: TableRendererProps) {
  return (
    <Card className="my-6 p-4 overflow-x-auto">
      <p className="font-semibold text-sm mb-3">{table.id}: {table.title}</p>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-muted">
            {table.headers.map((header, index) => (
              <th
                key={index}
                className="border border-border px-3 py-2 text-left font-semibold"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="even:bg-muted/50">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="border border-border px-3 py-2">
                  {String(cell ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.footnotes && table.footnotes.length > 0 && (
        <div className="mt-2 text-xs text-muted-foreground">
          {table.footnotes.map((note, index) => (
            <p key={index}>{note}</p>
          ))}
        </div>
      )}
    </Card>
  );
}
