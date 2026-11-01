using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using Accessibility;
class MSAAInvoke {
 [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)]out object result);
 [DllImport("oleacc.dll")] static extern int AccessibleChildren(IAccessible root,int start,int count,[Out,MarshalAs(UnmanagedType.LPArray,SizeParamIndex=2)] object[] children,out int obtained);
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [StructLayout(LayoutKind.Sequential)]struct Point{public int x,y;}
 [StructLayout(LayoutKind.Sequential)]struct Rect{public int left,top,right,bottom;}
 [DllImport("user32.dll")]static extern bool GetCursorPos(out Point p);
 [DllImport("user32.dll")]static extern bool GetWindowRect(IntPtr h,out Rect r);
 [StructLayout(LayoutKind.Sequential)]struct Message {public IntPtr hwnd;public uint message;public UIntPtr wp;public IntPtr lp;public uint time;public Point pt;public uint reserved;}
 [DllImport("user32.dll")]static extern bool PeekMessage(out Message m,IntPtr h,uint min,uint max,uint remove);
 [DllImport("user32.dll")]static extern bool TranslateMessage(ref Message m);
 [DllImport("user32.dll")]static extern IntPtr DispatchMessage(ref Message m);
 static void Pump(int milliseconds) {
  DateTime until=DateTime.UtcNow.AddMilliseconds(milliseconds);
  while(DateTime.UtcNow<until){Message m;while(PeekMessage(out m,IntPtr.Zero,0,0,1)){TranslateMessage(ref m);DispatchMessage(ref m);}System.Threading.Thread.Sleep(10);}
 }
 static List<IAccessible> found=new List<IAccessible>();static int nodes=0;
 static void Find(IAccessible a,string name,Rect bounds,int depth) {
  if(depth>40||nodes++>700)return;
  try {
   string n=a.get_accName(0),action=a.get_accDefaultAction(0);
   if(name=="dismiss-overlay") {
    int x,y,w,h;a.accLocation(out x,out y,out w,out h,0);
    if(String.IsNullOrEmpty(n)&&action=="点击"&&w>(bounds.right-bounds.left)*.8&&h>(bounds.bottom-bounds.top)*.8)found.Add(a);
   }else if(n==name&&!String.IsNullOrEmpty(action))found.Add(a);
  }catch{}
  int count=Math.Min(a.accChildCount,200);var children=new object[count];int got;
  AccessibleChildren(a,0,count,children,out got);
  for(int i=0;i<got;i++)if(children[i] is IAccessible)Find((IAccessible)children[i],name,bounds,depth+1);
 }
 [STAThread]static int Main(string[] args) {
  try {
   IntPtr hwnd=new IntPtr(long.Parse(args[0]));object root;Guid iid=new Guid("618736e0-3c3d-11cf-810c-00aa00389b71");
   int hr=AccessibleObjectFromWindow(hwnd,0xfffffffc,ref iid,out root);if(hr!=0)Marshal.ThrowExceptionForHR(hr);
   Rect bounds;GetWindowRect(hwnd,out bounds);
   Find((IAccessible)root,args[1]=="menu"?"\ue628":args[1],bounds,0);
   if(found.Count!=1)throw new Exception("Expected exactly one actionable target; got "+found.Count);
   IAccessible target=found[0];
   if(args.Length>2&&args[2]=="owner") {
    for(int i=0;i<3;i++) {
     string action=target.get_accDefaultAction(0)??"";
     if(action=="点击"||action.Equals("click",StringComparison.OrdinalIgnoreCase))break;
     target=target.accParent as IAccessible;
     if(target==null)throw new Exception("No clickable owner");
    }
    if((target.get_accDefaultAction(0)??"")!="点击")throw new Exception("Owner action was not a direct click");
   }
   Console.WriteLine("TARGET name="+target.get_accName(0)+" action="+target.get_accDefaultAction(0));
   var foreground=GetForegroundWindow();Point before,after;GetCursorPos(out before);
   target.accDoDefaultAction(0);Pump(1500);GetCursorPos(out after);
   Console.WriteLine("MSAA_INVOKED before="+foreground+" after="+GetForegroundWindow()+
                     " foreground_unchanged="+(foreground==GetForegroundWindow())+
                     " cursor_unchanged="+(before.x==after.x&&before.y==after.y));return 0;
  }catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}
 }
}
