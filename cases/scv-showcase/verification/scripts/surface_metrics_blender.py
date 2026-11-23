"""Area-sampled exact point-to-triangle diagnostics using Blender BVH."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def mesh(path):
    data = np.load(path)
    xyz, faces = data['vertices'],data['triangles']
    assert len(faces), str(path)
    return xyz,faces,BVHTree.FromPolygons(xyz.tolist(), faces.tolist(), all_triangles=True, epsilon=0)


def sample(xyz,faces,n,rng):
    tris = xyz[faces]
    areas = np.linalg.norm(np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]),axis=1)/2
    assert float(areas.sum())>0
    chosen = rng.choice(len(tris), size=n, p=areas/areas.sum())
    uv = rng.random((n,2))
    root = np.sqrt(uv[:,0])
    bary = np.column_stack((1-root,root*(1-uv[:,1]),root*uv[:,1]))
    return (tris[chosen]*bary[:,:,None]).sum(1)


def point_triangle_distances(point,tris):
    """Float64 closest distances, including skinny and degenerate triangles."""
    a,b,c=tris[:,0],tris[:,1],tris[:,2]
    normal=np.cross(b-a,c-a);n2=np.einsum('ij,ij->i',normal,normal)
    safe=np.maximum(n2,1e-300)
    u=np.einsum('ij,ij->i',np.cross(b-point,c-point),normal)/safe
    v=np.einsum('ij,ij->i',np.cross(c-point,a-point),normal)/safe
    w=1-u-v
    plane=np.square(np.einsum('ij,ij->i',point-a,normal))/safe
    edge=[]
    for x,y in [(a,b),(b,c),(c,a)]:
        direction=y-x;denom=np.einsum('ij,ij->i',direction,direction)
        t=np.clip(np.einsum('ij,ij->i',point-x,direction)/np.maximum(denom,1e-300),0,1)
        delta=point-(x+t[:,None]*direction)
        edge.append(np.einsum('ij,ij->i',delta,delta))
    edge=np.minimum.reduce(edge)
    return np.sqrt(np.where((n2>1e-30)&(u>=-1e-12)&(v>=-1e-12)&(w>=-1e-12),np.minimum(plane,edge),edge))


def distances(points,bvh,tris,diagonal):
    # Blender BVH uses float32. A conservative nearby candidate margin keeps
    # its skinny-triangle closest-point roundoff out of the final distances.
    margin=max(diagonal*1e-3,1e-6)
    result=[]
    for point in points:
        nearest=bvh.find_nearest(Vector(point))
        assert nearest[2] is not None,'Nearest-triangle query failed'
        candidates=bvh.find_nearest_range(Vector(point),nearest[3]+margin)
        indices={nearest[2]};indices.update(item[2] for item in candidates)
        result.append(float(point_triangle_distances(point,tris[list(indices)]).min()))
    return np.asarray(result,dtype=float)


def visible(points,bvh,cameras,diagonal):
    vis = np.zeros(len(points),dtype=bool)
    distance = max(diagonal*10,10)
    epsilon = max(diagonal*1e-5,1e-7)
    for view in cameras['views']:
        matrix=np.asarray(view['camera_to_world'],dtype=float)
        forward = -matrix[:3,2]
        forward /= np.linalg.norm(forward)
        for index in np.flatnonzero(~vis):
            point=points[index]
            hit=bvh.ray_cast(Vector(point-forward*distance),Vector(forward),distance+epsilon*2)
            if hit[0] is not None and np.linalg.norm(np.asarray(hit[0])-point)<epsilon:
                vis[index]=True
    return vis


def summarize(a,b,diag):
    if not len(a) or not len(b):
        return {'status':'no_visible_samples_in_one_or_both_meshes','reference_sample_count':len(a),'submission_sample_count':len(b),'fscore_by_reference_diagonal_fraction':{str(x):{'threshold_world_units':x*diag,'precision':None,'recall':None,'fscore':None} for x in [.005,.01,.02,.05]}}
    result={'mean_reference_to_submission':float(a.mean()),'mean_submission_to_reference':float(b.mean()),
        'symmetric_chamfer_l1':float((a.mean()+b.mean())/2),
        'symmetric_chamfer_l1_divided_by_reference_diagonal':float((a.mean()+b.mean())/2/diag),
        'symmetric_mean_squared_distance':float((np.square(a).mean()+np.square(b).mean())/2),
        'reference_to_submission_distance_percentiles':np.percentile(a,[50,90,95,99]).tolist(),
        'submission_to_reference_distance_percentiles':np.percentile(b,[50,90,95,99]).tolist(),
        'fscore_by_reference_diagonal_fraction':{}}
    for fraction in [.005,.01,.02,.05]:
        tau=fraction*diag
        recall=float((a<=tau).mean())
        precision=float((b<=tau).mean())
        fscore=2*recall*precision/(recall+precision) if recall+precision else 0
        result['fscore_by_reference_diagonal_fraction'][str(fraction)]={'threshold_world_units':tau,'precision':precision,'recall':recall,'fscore':fscore}
    return result


def main():
    argv=sys.argv[sys.argv.index('--')+1:]
    p=argparse.ArgumentParser()
    p.add_argument('--reference',required=True)
    p.add_argument('--submission',required=True)
    p.add_argument('--cameras',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--samples',type=int,default=50000)
    args=p.parse_args(argv)
    ref,rf,rb=mesh(args.reference)
    sub,sf,sb=mesh(args.submission)
    diag=float(np.linalg.norm(np.ptp(ref,axis=0)))
    rng=np.random.default_rng(20261122)
    points_r=sample(ref,rf,args.samples,rng)
    points_s=sample(sub,sf,args.samples,rng)
    a,b=distances(points_r,sb,sub[sf],diag),distances(points_s,rb,ref[rf],diag)
    cameras=json.loads(Path(args.cameras).read_text(encoding='utf-8'))
    vr,vs=visible(points_r,rb,cameras,diag),visible(points_s,sb,cameras,diag)
    identity=distances(points_r[:2000],rb,ref[rf],diag)
    assert identity.max()<diag*1e-5, identity.max()
    result={'status':'raw_diagnostics_not_calibrated_score','alignment':'Fixed input coordinates; no ICP or registration',
        'method':'Triangle-area weighted random surface sampling; BVH nearest/nearby triangle candidates followed by float64 point-to-triangle distance recomputation. Both directions.',
        'BVH_float32_candidate_distance_margin_reference_diagonal_fraction':.001,
        'sample_count_per_mesh':args.samples,'random_seed':20261122,
        'reference_bounding_box_diagonal':diag,'all_surface':summarize(a,b,diag),
        'reference_visible_sample_fraction':float(vr.mean()),'submission_visible_sample_fraction':float(vs.mean()),
        'six_input_view_visible_samples':summarize(a[vr],b[vs],diag),
        'control_reference_self_distance_max':float(identity.max()),
        'visibility_method':'A sampled surface point must be the first BVH intersection from at least one input orthographic direction. Filters tested sample points only; nearest target uses entire mesh.',
        'limitations':['Whole-surface numbers include reference-hidden surfaces and are diagnostic, not a fair standalone score.',
            'Visible-sample metrics also do not resolve every ambiguity in occluded geometry. Thresholds are reported at several scales, not selected after seeing a result.',
            'This file reports raw geometry metrics; the frozen scoring rules combine visible F1 at 0.5% with six-view silhouette IoU.']}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('SURFACE_DIAGNOSTICS_COMPLETE',flush=True)


if __name__=='__main__': main()
