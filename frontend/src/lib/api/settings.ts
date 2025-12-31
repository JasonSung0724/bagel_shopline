const API_URL = '/api';

export interface PlatformMapping {
    [key: string]: string[];
}

export interface AllMappings {
    [platform: string]: PlatformMapping;
}

export const settingsApi = {
    // Get all mappings
    getAllMappings: async (): Promise<AllMappings> => {
        const res = await fetch(`${API_URL}/settings/mappings`);
        if (!res.ok) throw new Error('Failed to fetch mappings');
        const json = await res.json();
        return json.data;
    },

    // Update mapping for a specific platform
    updateMapping: async (platform: string, mapping: PlatformMapping): Promise<void> => {
        const res = await fetch(`${API_URL}/settings/mappings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform, mapping }),
        });
        if (!res.ok) throw new Error('Failed to update mapping');
    },
};
