
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

// Assuming NewProduct interface is defined elsewhere or will be added.
// For example:
// export interface NewProduct {
//     code: string;
//     name: string;
//     qty: number;
// }

const API_BASE = '/api';

export const productApi = {
    getAll: async (): Promise<Product[]> => {
        const res = await fetch(`${API_BASE}/products`);
        if (!res.ok) throw new Error('Failed to fetch products');
        return res.json();
    },

    create: async (product: any /* NewProduct */): Promise<Product> => { // Changed type to 'any' to avoid compile error without NewProduct definition
        const res = await fetch(`${API_BASE}/products`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(product),
        });
        if (!res.ok) throw new Error('Failed to create product');
        return res.json();
    },

    updateQty: async (code: string, qty: number): Promise<Product> => {
        const res = await fetch(`${API_BASE}/products/${code}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qty }),
        });
        if (!res.ok) throw new Error('Failed to update product');
        return res.json();
    },

    delete: async (code: string): Promise<void> => {
        const res = await fetch(`${API_BASE}/products/${code}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete product');
    },

    addAlias: async (code: string, alias: string): Promise<Product> => {
        const res = await fetch(`${API_BASE}/products/${code}/aliases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ alias }),
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
