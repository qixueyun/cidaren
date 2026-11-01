using System;
using System.Runtime.InteropServices;
using Accessibility;
class InspectMSAA {
 [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)]out object result);
 [DllImport("oleacc.dll")] static extern int AccessibleChildren(IAccessible root,int start,int count,[Out,MarshalAs(UnmanagedType.LPArray,SizeParamIndex=2)] object[] children,out int obtained);
 static int nodes=0;
 static void Walk(IAccessible a,string path,int depth) {
  if(depth>35||nodes++>500)return;
  try{Console.WriteLine(path+"|"+a.get_accName(0)+"|"+a.get_accDefaultAction(0));}catch{}
  int count=Math.Min(a.accChildCount,200);var children=new object[count];int got;
  AccessibleChildren(a,0,count,children,out got);
  for(int i=0;i<got;i++) {
   if(children[i] is IAccessible)Walk((IAccessible)children[i],path+"/"+i,depth+1);
   else try{Console.WriteLine(path+"/"+i+"|"+a.get_accName(children[i])+"|"+a.get_accDefaultAction(children[i]));}catch{}
  }
 }
 [STAThread] static int Main(string[] args) {
  object root;Guid iid=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71");
  int hr=AccessibleObjectFromWindow(new IntPtr(long.Parse(args[0])),0xfffffffc,ref iid,out root);
  if(hr!=0){Console.Error.WriteLine("MSAA error "+hr);return 1;}
  Walk((IAccessible)root,"root",0);return 0;
 }
}
