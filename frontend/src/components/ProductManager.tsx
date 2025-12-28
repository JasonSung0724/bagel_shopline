import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Edit2, Save, X, Tag, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { Product, productApi } from '@/lib/api/product';

export default function ProductManager() {
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');

    // Expanded rows for aliases
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

    // Editing states
    const [editingCode, setEditingCode] = useState<string | null>(null);
    const [editQty, setEditQty] = useState<number>(0);
    const [newAlias, setNewAlias] = useState('');

    // Creating states
    const [isCreating, setIsCreating] = useState(false);
    const [newProduct, setNewProduct] = useState({ code: '', name: '', qty: 1 });

    const loadProducts = useCallback(async () => {
        try {
            setLoading(true);
            const data = await productApi.getAll();
            setProducts(data);
            setError(null);
        } catch (err) {
            setError('無法載入產品資料');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadProducts();
    }, [loadProducts]);

    const toggleExpand = (code: string) => {
        const newSet = new Set(expandedRows);
        if (newSet.has(code)) {
            newSet.delete(code);
        } else {
            newSet.add(code);
        }
        setExpandedRows(newSet);
    };

    const handleUpdateQty = async (code: string) => {
        try {
            await productApi.updateQty(code, editQty);
            setEditingCode(null);
            loadProducts();
        } catch (err) {
            alert('更新失敗');
        }
    };

    const handleDeleteProduct = async (code: string) => {
        if (!confirm('確定要刪除此產品及其所有別名嗎？')) return;
        try {
            await productApi.delete(code);
            loadProducts();
        } catch (err) {
            alert('刪除失敗');
        }
    };

    const handleCreateProduct = async () => {
        if (!newProduct.code) return;
        try {
            await productApi.create({
                code: newProduct.code,
                name: newProduct.name || newProduct.code,
                qty: newProduct.qty
            });
            setIsCreating(false);
            setNewProduct({ code: '', name: '', qty: 1 });
            loadProducts();
        } catch (err) {
            alert('建立失敗，代碼可能重複');
        }
    };

    const handleAddAlias = async (code: string) => {
        if (!newAlias.trim()) return;
        try {
            await productApi.addAlias(code, newAlias);
            setNewAlias('');
            loadProducts();
        } catch (err) {
            alert('新增別名失敗');
        }
    };

    const handleDeleteAlias = async (aliasId: number) => {
        if (!confirm('確定刪除此關鍵字？')) return;
        try {
            await productApi.deleteAlias(aliasId);
            loadProducts();
        } catch (err) {
            alert('刪除失敗');
        }
    };

    const filteredProducts = products.filter(p =>
        p.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.aliases.some(a => a.alias.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    if (loading) return <div className="p-4 flex justify-center"><Loader2 className="animate-spin text-green-500" /></div>;

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-gray-700">產品與別名管理</h3>
                <button
                    onClick={() => setIsCreating(true)}
                    className="btn-primary flex items-center gap-2 px-3 py-2 text-sm"
                >
                    <Plus className="w-4 h-4" /> 新增產品
                </button>
            </div>

            {error && <div className="mb-4 text-red-500 bg-red-50 p-3 rounded">{error}</div>}

            {/* Creating Form */}
            {isCreating && (
                <div className="mb-6 p-4 bg-green-50 rounded-lg border border-green-200">
                    <h3 className="text-sm font-semibold text-green-800 mb-3">新增產品</h3>
                    <div className="flex flex-wrap gap-3 items-end">
                        <div>
                            <label className="text-xs text-gray-600 block mb-1">產品代碼 *</label>
                            <input
                                value={newProduct.code}
                                onChange={e => setNewProduct({ ...newProduct, code: e.target.value })}
                                className="input-field w-40"
                                placeholder="bagel001"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-gray-600 block mb-1">產品名稱</label>
                            <input
                                value={newProduct.name}
                                onChange={e => setNewProduct({ ...newProduct, name: e.target.value })}
                                className="input-field w-40"
                                placeholder="原味貝果"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-gray-600 block mb-1">每箱數量</label>
                            <input
                                type="number"
                                value={newProduct.qty}
                                onChange={e => setNewProduct({ ...newProduct, qty: parseInt(e.target.value) || 0 })}
                                className="input-field w-24"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button onClick={handleCreateProduct} className="btn-primary py-2 px-4">儲存</button>
                            <button onClick={() => setIsCreating(false)} className="px-3 py-2 text-gray-500 hover:text-gray-700">取消</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Search */}
            <div className="mb-4">
                <input
                    type="text"
                    placeholder="搜尋代碼、名稱或關鍵字..."
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                />
            </div>

            {/* List */}
            <div className="space-y-2">
                {filteredProducts.map(product => (
                    <div key={product.code} className="border rounded-lg overflow-hidden bg-white hover:shadow-sm transition-shadow">
                        <div className="p-3 flex items-center justify-between bg-gray-50 border-b">
                            <div className="flex items-center gap-4 flex-1">
                                <button onClick={() => toggleExpand(product.code)} className="text-gray-500 hover:text-green-600">
                                    {expandedRows.has(product.code) ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                </button>
                                <div className="font-mono font-bold text-gray-700 w-32">{product.code}</div>
                                <div className="text-gray-600 flex-1">{product.name}</div>

                                {/* Qty Editing */}
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-gray-500">Qty:</span>
                                    {editingCode === product.code ? (
                                        <div className="flex items-center gap-1">
                                            <input
                                                type="number"
                                                value={editQty}
                                                onChange={e => setEditQty(parseInt(e.target.value) || 0)}
                                                className="w-16 px-1 py-0.5 border rounded text-sm"
                                                autoFocus
                                            />
                                            <button onClick={() => handleUpdateQty(product.code)}><Save className="w-4 h-4 text-green-600" /></button>
                                            <button onClick={() => setEditingCode(null)}><X className="w-4 h-4 text-gray-400" /></button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 group">
                                            <span className="font-mono">{product.qty}</span>
                                            <button
                                                onClick={() => { setEditingCode(product.code); setEditQty(product.qty); }}
                                                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-600"
                                            >
                                                <Edit2 className="w-3 h-3" />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <button onClick={() => handleDeleteProduct(product.code)} className="ml-4 text-gray-400 hover:text-red-500">
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Aliases (Detailed View) */}
                        {expandedRows.has(product.code) && (
                            <div className="p-4 bg-white">
                                <div className="text-xs text-gray-500 mb-2 font-semibold flex items-center gap-1">
                                    <Tag className="w-3 h-3" /> 搜尋關鍵字 (Aliases)
                                </div>
                                <div className="flex flex-wrap gap-2 mb-3">
                                    {product.aliases.map(alias => (
                                        <span key={alias.id} className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-50 text-yellow-700 border border-yellow-200 rounded text-xs">
                                            {alias.alias}
                                            <button
                                                onClick={() => handleDeleteAlias(alias.id)}
                                                className="hover:text-red-500"
                                            >
                                                <X className="w-3 h-3" />
                                            </button>
                                        </span>
                                    ))}
                                    {product.aliases.length === 0 && <span className="text-gray-400 text-xs italic">無關鍵字</span>}
                                </div>

                                {/* Add Alias */}
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        placeholder="新增關鍵字 (例如: 巧克力貝果)"
                                        value={newAlias}
                                        onChange={e => setNewAlias(e.target.value)}
                                        className="flex-1 px-2 py-1 border rounded text-sm focus:ring-1 focus:ring-green-500"
                                        onKeyDown={e => {
                                            if (e.key === 'Enter') handleAddAlias(product.code);
                                        }}
                                    />
                                    <button
                                        onClick={() => handleAddAlias(product.code)}
                                        disabled={!newAlias.trim()}
                                        className="px-3 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200 disabled:opacity-50"
                                    >
                                        新增
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                ))}

                {filteredProducts.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                        找不到相關產品
                    </div>
                )}
            </div>
        </div>
    );
}
