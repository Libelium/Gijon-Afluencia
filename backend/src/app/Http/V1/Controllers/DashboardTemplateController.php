<?php

namespace App\Http\V1\Controllers;

use App\Models\Dashboard;
use App\Models\Device;
use App\Models\Entity;
use App\Models\EntityGroup;
use App\Http\V1\Resources\DeviceFullResource;
use Illuminate\Http\Request;

/**
 * A dashboard template's configuration: its type, settings, and the sets of entities,
 * devices, groups and regulation that feed it. Independent of the dashboard's own actions.
 */
class DashboardTemplateController extends Controller
{
    public function setTemplateType(Request $request, $id)
    {
        $request->validate([
            'template_type' => 'required|string|max:255|min:3',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if ($dashboard->template) {
            return response()->json([
                'message' => 'Dashboard already has a template',
            ], 400);
        } else {
            $dashboard->template()->create([
                'template_type' => $request->template_type,
            ]);
        }

        return response()->json($dashboard, 200);
    }

    public function setTemplateConfig(Request $request, $id)
    {
        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template()->update([
            'config' => $request->config,
            'template_type' => $dashboard->template->template_type,
        ]);

        return response()->json($dashboard, 200);
    }

    public function setTemplateEntities(Request $request, $id)
    {
        $request->validate([
            'entities' => 'required|array',
            'entities.*' => 'required|numeric',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->entities()->delete();

        foreach ($request->entities as $entity) {

            $this->authorize('read', Entity::find($entity));
            $dashboard->template->entities()->create([
                'entity_id' => $entity,
            ]);
        }
    }

    public function setTemplateDevices(Request $request, $id)
    {
        $request->validate([
            'devices' => 'required|array',
            'devices.*' => 'required|numeric',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->devices()->delete();

        foreach ($request->devices as $device) {

            $this->authorize('read', Device::find($device));
            $dashboard->template->devices()->create([
                'device_id' => $device,
            ]);
        }

        $newDevices = $dashboard->template->devices()->with('device')->get();

        $newDevices = $newDevices->pluck('device');

        return DeviceFullResource::collection($newDevices);
    }

    public function setTemplateGroups(Request $request, $id)
    {
        $request->validate([
            'groups' => 'required|array',
            'groups.*' => 'required|numeric',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->groups()->delete();

        foreach ($request->groups as $group) {

            $this->authorize('read', EntityGroup::find($group));
            $dashboard->template->groups()->create([
                'group_id' => $group,
            ]);
        }
    }

    public function setTemplateRegulation(Request $request, $id)
    {
        if ($request->input('regulation_id') < 0) {
            $request->merge(['regulation_id' => null]);
        }

        $request->validate([
            'regulation_id' => 'nullable|exists:regulations,id',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->regulation_id = $request->regulation_id;
        $dashboard->template->save();

        return response()->json($dashboard, 200);
    }
}
