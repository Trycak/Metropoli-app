import React, { useState, useEffect, useMemo } from 'react';
import { ShoppingCart, Package, DollarSign, BarChart2, Plus, X, List, Trash2, Users, Loader, Coffee, AlertTriangle } from 'lucide-react';

// --- FIREBASE IMPORTS ---
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, doc, setDoc, onSnapshot } from 'firebase/firestore';

// --- CONFIGURACIONES ---
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : null;

const ACCENT_COLOR_HEX = '#279aa0';
const PRIMARY_COLOR_BG = `bg-[${ACCENT_COLOR_HEX}]`;

const initialProducts = [
  { id: 101, name: 'Entrada', price: 2000.00, stock: 500 },
];

const initialAccounts = [
  { id: Date.now(), name: 'Venta 1', items: [], time: Date.now() },
];

// --- COMPONENTE LOGO ---
const Logo = () => {
    const logoImageUrl = "https://www.fecobacr.com/wp-content/uploads/2025/06/LSB-Metropoli.jpg";
    return (
        <div className="flex items-center space-x-2 p-4">
            <img 
                src={logoImageUrl} 
                alt="Logo" 
                className="w-10 h-10 object-contain rounded-full border-2 border-white shadow-md"
            />
            <h1 className="text-xl font-black text-white leading-tight">MBA Cafe</h1>
        </div>
    );
};

// --- MODAL ---
const Modal = ({ title, onClose, children }) => (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center border-b pb-3 mb-4">
          <h3 className="text-xl font-bold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>
        {children}
      </div>
    </div>
);

export const App = () => {
  const [db, setDb] = useState(null);
  const [userId, setUserId] = useState(null);
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const [products, setProducts] = useState(initialProducts);
  const [salesHistory, setSalesHistory] = useState([]);
  const [openAccounts, setOpenAccounts] = useState(initialAccounts);
  const [activeAccountId, setActiveAccountId] = useState(initialAccounts[0]?.id || null);
  const [lastSaleNumber, setLastSaleNumber] = useState(0);

  const [activeTab, setActiveTab] = useState('pos');
  const [saleMessage, setSaleMessage] = useState('');
  const [newAccountName, setNewAccountName] = useState('');
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // --- FIREBASE LOGIC ---
  useEffect(() => {
    if (!firebaseConfig) { setIsLoading(false); return; }
    const app = initializeApp(firebaseConfig);
    const dbInstance = getFirestore(app);
    const authInstance = getAuth(app);
    setDb(dbInstance);

    onAuthStateChanged(authInstance, async (user) => {
        if (user) { setUserId(user.uid); } 
        else {
            try {
                const anonymousUser = await signInAnonymously(authInstance);
                setUserId(anonymousUser.user.uid);
            } catch (error) { setUserId(crypto.randomUUID()); }
        }
        setIsAuthReady(true);
    });
  }, []);

  useEffect(() => {
      if (!db || !userId || !isAuthReady) return; 
      const docRef = doc(db, 'artifacts', appId, 'users', userId, 'pos_data', 'appState');
      const unsubscribe = onSnapshot(docRef, (docSnapshot) => {
          if (docSnapshot.exists()) {
              const data = docSnapshot.data();
              setProducts(data.products || initialProducts);
              setSalesHistory(data.salesHistory || []);
              setOpenAccounts(data.openAccounts || initialAccounts);
              setLastSaleNumber(data.lastSaleNumber || 0); 
              setActiveAccountId(data.activeAccountId || data.openAccounts?.[0]?.id || null);
          } else {
              setDoc(docRef, { products: initialProducts, salesHistory: [], openAccounts: initialAccounts, activeAccountId: initialAccounts[0]?.id || null, lastSaleNumber: 1 });
          }
          setIsLoading(false);
      });
      return () => unsubscribe();
  }, [db, userId, isAuthReady]);

  const saveState = async (updates = {}) => {
    if (!db || !userId) return;
    const stateToSave = {
        products: updates.products !== undefined ? updates.products : products,
        salesHistory: updates.salesHistory !== undefined ? updates.salesHistory : salesHistory,
        openAccounts: updates.openAccounts !== undefined ? updates.openAccounts : openAccounts,
        activeAccountId: updates.activeAccountId !== undefined ? updates.activeAccountId : activeAccountId,
        lastSaleNumber: updates.lastSaleNumber !== undefined ? updates.lastSaleNumber : lastSaleNumber,
    };
    await setDoc(doc(db, 'artifacts', appId, 'users', userId, 'pos_data', 'appState'), stateToSave);
  };

  const activeAccount = openAccounts.find(acc => acc.id === activeAccountId);
  const currentCart = activeAccount?.items || [];
  const total = currentCart.reduce((acc, item) => acc + item.price * item.quantity, 0);

  const addAccount = (name) => {
    let finalName = name.trim();
    let nextNum = lastSaleNumber;
    if (!finalName) { nextNum = lastSaleNumber + 1; finalName = 'Venta ' + nextNum; }
    const newId = Date.now();
    saveState({ openAccounts: [...openAccounts, { id: newId, name: finalName, items: [], time: newId }], activeAccountId: newId, lastSaleNumber: nextNum });
  };

  const addToCart = (product) => {
    if (!activeAccount || product.stock <= 0) return;
    const updatedAccounts = openAccounts.map(acc => {
      if (acc.id === activeAccountId) {
        const exist = acc.items.find(i => i.id === product.id);
        const items = exist ? acc.items.map(i => i.id === product.id ? { ...i, quantity: i.quantity + 1 } : i) : [...acc.items, { ...product, quantity: 1 }];
        return { ...acc, items };
      }
      return acc;
    });
    saveState({ openAccounts: updatedAccounts });
  };

  const completeSale = (method) => { 
    if (currentCart.length === 0) return;
    const newSale = { id: Date.now(), timestamp: new Date().toLocaleTimeString(), accountName: activeAccount.name, items: currentCart, total, payment: method };
    const updatedProducts = products.map(p => {
        const item = currentCart.find(i => i.id === p.id);
        return item ? { ...p, stock: Math.max(0, p.stock - item.quantity) } : p;
    });
    saveState({ salesHistory: [newSale, ...salesHistory], products: updatedProducts, openAccounts: openAccounts.filter(a => a.id !== activeAccountId), activeAccountId: openAccounts.filter(a => a.id !== activeAccountId)[0]?.id || null });
    setSaleMessage('Venta guardada');
    setTimeout(() => setSaleMessage(''), 3000);
  };

  // --- FILA DE INVENTARIO REPARADA ---
  const ProductRow = ({ product }) => {
    const [p, setP] = useState(product.price.toString());
    const [s, setS] = useState(product.stock.toString());

    useEffect(() => {
        if (document.activeElement?.id !== 'p' + product.id) setP(product.price.toString());
        if (document.activeElement?.id !== 's' + product.id) setS(product.stock.toString());
    }, [product.price, product.stock]);

    return (
        <tr className="border-b hover:bg-gray-50">
            <td className="p-4 font-medium">{product.name}</td>
            <td className="p-4"><input id={'p'+product.id} type="number" value={p} onChange={e=>setP(e.target.value)} onBlur={()=>saveState({products: products.map(x=>x.id===product.id?{...x, price: parseFloat(p)}:x)})} className="w-24 p-1 border rounded" /></td>
            <td className="p-4"><input id={'s'+product.id} type="number" value={s} onChange={e=>setS(e.target.value)} onBlur={()=>saveState({products: products.map(x=>x.id===product.id?{...x, stock: parseInt(s)}:x)})} className="w-20 p-1 border rounded" /></td>
            <td className="p-4 text-center"><button onClick={()=>{setProductToDelete(product); setIsDeleteModalOpen(true)}} className="text-red-500 hover:bg-red-50 p-2 rounded-full"><Trash2 className="w-5 h-5" /></button></td>
        </tr>
    );
  };

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      <div className={`w-20 md:w-64 flex flex-col ${PRIMARY_COLOR_BG}`}>
        <Logo />
        <nav className="mt-8 p-2 space-y-2">
            <button onClick={()=>setActiveTab('pos')} className={`flex items-center w-full p-3 rounded-xl text-white ${activeTab==='pos'?'bg-white !text-[#279aa0] font-bold':''}`}><ShoppingCart className="w-5 h-5 md:mr-3"/><span className="hidden md:inline">Ventas</span></button>
            <button onClick={()=>setActiveTab('inv')} className={`flex items-center w-full p-3 rounded-xl text-white ${activeTab==='inv'?'bg-white !text-[#279aa0] font-bold':''}`}><Package className="w-5 h-5 md:mr-3"/><span className="hidden md:inline">Inventario</span></button>
        </nav>
      </div>
      <main className="flex-grow overflow-hidden">
        {activeTab === 'pos' ? (
          <div className="flex h-full">
            <div className="w-1/4 p-4 border-r bg-white overflow-y-auto">
              <h2 className="font-bold mb-4">Pedidos</h2>
              <button onClick={()=>addAccount('')} className="w-full py-2 bg-[#279aa01a] text-[#279aa0] border border-[#279aa0] rounded-lg mb-4 font-bold">+ Nuevo</button>
              {openAccounts.map(a=>(<div key={a.id} onClick={()=>saveState({activeAccountId:a.id})} className={`p-3 rounded-lg mb-2 cursor-pointer ${activeAccountId===a.id?'bg-[#279aa0] text-white':'bg-gray-100'}`}>{a.name}</div>))}
            </div>
            <div className="w-2/4 p-4 overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                  <h1 className="text-2xl font-bold">{activeAccount?.name || 'Seleccione Cuenta'}</h1>
                  {saleMessage && <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm">{saleMessage}</span>}
              </div>
              <div className="grid grid-cols-2 gap-4">
                {products.map(p=>(
                    <button key={p.id} onClick={()=>addToCart(p)} className="p-4 border rounded-xl bg-white hover:border-[#279aa0] text-left">
                        <p className="font-bold">{p.name}</p>
                        <p className="text-xs text-gray-500">{p.stock} disponibles</p> 
                        <p className="text-lg font-bold mt-2">C{p.price}</p>
                    </button>
                ))}
              </div>
            </div>
            <div className="w-1/4 p-4 bg-gray-50 flex flex-col">
              <h2 className="font-bold mb-4">Carrito</h2>
              <div className="flex-grow overflow-y-auto">{currentCart.map(i=>(<div key={i.id} className="flex justify-between text-sm mb-2 border-b pb-1"><span>{i.name} x{i.quantity}</span><span>C{i.price*i.quantity}</span></div>))}</div>
              <div className="text-xl font-bold border-t pt-4 mb-4 flex justify-between"><span>Total:</span><span>C{total}</span></div>
              <button onClick={()=>completeSale('Efectivo')} className="w-full py-3 bg-green-600 text-white rounded-xl font-bold mb-2">Efectivo</button>
              <button onClick={()=>completeSale('SINPE')} className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold">SINPE</button>
            </div>
          </div>
        ) : (
          <div className="p-8 overflow-y-auto h-full">
            <h1 className="text-2xl font-bold mb-6">Inventario</h1>
            <table className="w-full bg-white rounded-xl shadow overflow-hidden">
              <thead className="bg-gray-50 text-left">
                <tr><th className="p-4">Producto</th><th className="p-4">Precio</th><th className="p-4">Stock</th><th className="p-4 text-center">Accion</th></tr>
              </thead>
              <tbody>{products.map(p=><ProductRow key={p.id} product={p}/>)}</tbody>
            </table>
          </div>
        )}
      </main>
      {isDeleteModalOpen && (
          <Modal title="Eliminar" onClose={()=>setIsDeleteModalOpen(false)}>
              <p className="mb-4">Desea eliminar {productToDelete?.name}?</p>
              <button onClick={()=>{saveState({products:products.filter(x=>x.id!==productToDelete.id)}); setIsDeleteModalOpen(false)}} className="w-full py-2 bg-red-600 text-white rounded font-bold">Confirmar</button>
          </Modal>
      )}
    </div>
  );
};

export default App;
