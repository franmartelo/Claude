import sys, time, numpy as np, cv2, onnxruntime as ort
S='/tmp/claude-0/-home-user-Claude/559bbc7f-ba77-553d-93c3-9e7cab1bef04/scratchpad/'
sess=ort.InferenceSession(S+'models/x2.onnx', providers=['CPUExecutionProvider'])
def sr2(img, tile=256, pad=16):
    h,w=img.shape[:2]; x=img[...,::-1].astype(np.float32)/255.
    out=np.zeros((h*2,w*2,3),np.float32)
    for y0 in range(0,h,tile):
        for x0 in range(0,w,tile):
            y1,x1=min(y0+tile,h),min(x0+tile,w)
            a0,b0=max(y0-pad,0),max(x0-pad,0); a1,b1=min(y1+pad,h),min(x1+pad,w)
            t=x[a0:a1,b0:b1]
            ph,pw=(t.shape[0]%2),(t.shape[1]%2)
            if ph or pw: t=np.pad(t,((0,ph),(0,pw),(0,0)),mode='reflect')
            r=sess.run(None,{'input':t.transpose(2,0,1)[None]})[0][0].transpose(1,2,0)
            out[y0*2:y1*2,x0*2:x1*2]=r[(y0-a0)*2:(y0-a0)*2+(y1-y0)*2,(x0-b0)*2:(x0-b0)*2+(x1-x0)*2]
    return (np.clip(out,0,1)*255+.5).astype(np.uint8)[...,::-1]
if __name__=='__main__':
    t=time.time(); img=cv2.imread(sys.argv[1]); o=sr2(img); cv2.imwrite(sys.argv[2],o,[cv2.IMWRITE_JPEG_QUALITY,95]); print(img.shape,'->',o.shape,'%.1fs'%(time.time()-t))
