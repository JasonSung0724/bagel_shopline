
export interface ProductAlias {
    id: number;
    product_code: string;
    alias: string;
    created_at?: string;
}

export interface Product {
    code: string;
    name: string;
    qty: number;
    aliases: ProductAlias[];
    created_at?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8082';

export const productApi = {
    getAll: async (): Promise<Product[]> => {
        const res = await fetch(`${API_BASE}/api/products`);
        if (!res.ok) throw new Error('Failed to fetch products');
        return res.json();
    },

    create: async (code: string, name: string, qty: number): Promise<Product> => {
        const res = await fetch(`${API_BASE}/api/products`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, name, qty }),
        });
        if (!res.ok) throw new Error('Failed to create product');
        return res.json();
    },

    updateQty: async (code: string, qty: number): Promise<Product> => {
        const res = await fetch(`${API_BASE}/api/products/${code}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qty }),
        });
        if (!res.ok) throw new Error('Failed to update product');
        return res.json();
    },

    delete: async (code: string): Promise<boolean> => {
        const res = await fetch(`${API_BASE}/api/products/${code}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete product');
        return (await res.json()).success;
    },

    addAlias: async (product_code: string, alias: string): Promise<ProductAlias> => {
        const res = await fetch(`${API_BASE}/api/aliases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_code, alias }),
        });
        if (!res.ok) throw new Error('Failed to add alias');
        return res.json();
    },

    deleteAlias: async (alias_id: number): Promise<boolean> => {
        const res = await fetch(`${API_BASE}/api/aliases/${alias_id}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete alias');
        return (await res.json()).success;
    },
};
