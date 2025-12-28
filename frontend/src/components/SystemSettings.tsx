import { useState } from 'react';
import ProductManager from './ProductManager';
import MappingEditor from './MappingEditor';
import { Database, Settings, X } from 'lucide-react';

interface Props {
    onClose: () => void;
}

export default function SystemSettings({ onClose }: Props) {
    const [activeTab, setActiveTab] = useState<'products' | 'mappings'>('products');

    return (
        <div className="card mt-8 border-t-4 border-t-blue-500 shadow-lg">
            <div className="flex justify-between items-center p-4 border-b bg-gray-50">
                <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-gray-500" />
                    系統設定 (System Settings)
                </h2>
                <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                    <X className="w-5 h-5 text-gray-500" />
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b">
                <button
                    className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 border-b-2 transition-colors ${activeTab === 'products'
                            ? 'border-blue-500 text-blue-600 bg-blue-50'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                        }`}
                    onClick={() => setActiveTab('products')}
                >
                    <Database className="w-4 h-4" /> 產品資料庫
                </button>
                <button
                    className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 border-b-2 transition-colors ${activeTab === 'mappings'
                            ? 'border-green-500 text-green-600 bg-green-50'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                        }`}
                    onClick={() => setActiveTab('mappings')}
                >
                    <Settings className="w-4 h-4" /> 欄位對應設定
                </button>
            </div>

            {/* Content */}
            <div className="p-6">
                {activeTab === 'products' ? (
                    <ProductManager />
                ) : (
                    <MappingEditor />
                )}
            </div>
        </div>
    );
}
