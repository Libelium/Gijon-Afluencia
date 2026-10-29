<?php

namespace App\Http\V1\Controllers\OutConnectors;

use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Requests\OutConnectors\MqttConnectorRequest;
use App\Http\V1\Resources\OutConnectors\OutConnectorResource;
use App\Models\OutConnectors\MqttConnector;
use App\Models\OutConnectors\OutConnector;
use App\Repositories\ResourcePermissionRepository;

class MqttConnectorController extends Controller
{
    public const TYPE = 'mqtt';

    public function store(MqttConnectorRequest $request)
    {
        $this->authorize('create', OutConnector::class);

        $certificate = $request->clientCertificateData();

        $outConnector = DB::transaction(function () use ($request, $certificate) {
            $mqttConnector = MqttConnector::create(
                $request->connectorData() + $certificate + ['password' => $request->input('password')]
            );

            $outConnector = new OutConnector([
                'name' => $request->input('name'),
                'type' => self::TYPE,
                'status' => 'active',
                'user_id' => Auth::id(),
                'use_readable_names' => $request->boolean('use_readable_names'),
            ]);
            $outConnector->connectable()->associate($mqttConnector);
            $outConnector->save();

            ResourcePermissionRepository::assignDefaultResourcePermissions(Auth::user(), $outConnector);

            return $outConnector;
        });

        return (new OutConnectorResource($outConnector->load('connectable')))
            ->response()
            ->setStatusCode(201);
    }

    /**
     * @param int $id Id of the out connector, the same one show and destroy use.
     */
    public function update(MqttConnectorRequest $request, int $id)
    {
        $outConnector = OutConnector::with('connectable')->findOrFail($id);

        $this->authorize('update', $outConnector);

        $mqttConnector = $outConnector->connectable;
        if (!$mqttConnector instanceof MqttConnector) {
            abort(404);
        }

        $certificate = $request->clientCertificateData($mqttConnector);

        DB::transaction(function () use ($request, $outConnector, $mqttConnector, $certificate) {
            $data = $request->connectorData() + $certificate;
            // The API never returns the password, so an empty one means "keep the current".
            if ($request->filled('password')) {
                $data['password'] = $request->input('password');
            }
            $mqttConnector->update($data);

            $outConnector->update([
                'name' => $request->input('name'),
                'use_readable_names' => $request->boolean('use_readable_names'),
            ]);
        });

        return (new OutConnectorResource($outConnector->refresh()->load('connectable')))->response();
    }
}
