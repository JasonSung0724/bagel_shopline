const API_URL = '/api';

// Unified column mappings: { field_name: [alias1, alias2, ...] }
export interface ColumnMappings {
    [fieldName: string]: string[];
}

export const settingsApi = {
    // Get unified column mappings
    getMappings: async (): Promise<ColumnMappings> => {
        const res = await fetch(`${API_URL}/settings/mappings`);
        if (!res.ok) throw new Error('Failed to fetch mappings');
        const json = await res.json();
        return json.data;
    },

    // Update all mappings
    updateMappings: async (mappings: ColumnMappings): Promise<void> => {
        const res = await fetch(`${API_URL}/settings/mappings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mappings),
        });
        if (!res.ok) throw new Error('Failed to update mappings');
    },

    // Update aliases for a single field
    updateFieldAliases: async (fieldName: string, aliases: string[]): Promise<void> => {
        const res = await fetch(`${API_URL}/settings/mappings/${encodeURIComponent(fieldName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ aliases }),
        });
        if (!res.ok) throw new Error('Failed to update field aliases');
    },
};
